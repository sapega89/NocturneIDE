# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing specialized line edits.
"""

import enum

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QHBoxLayout,
    QLayout,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)


class EricLineEditSideWidget(QWidget):
    """
    Class implementing the side widgets for the line edit class.

    @signal sizeHintChanged() emitted to indicate a change of the size hint
    """

    sizeHintChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

    def event(self, evt):
        """
        Public method to handle events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating, whether the event was recognized
        @rtype bool
        """
        if evt.type() == QEvent.Type.LayoutRequest:
            self.sizeHintChanged.emit()
        return QWidget.event(self, evt)


class EricLineEditSide(enum.Enum):
    """
    Class defining the line edit sides.
    """

    LEFT = 0
    RIGHT = 1


class EricLineEdit(QLineEdit):
    """
    Class implementing a line edit widget showing some inactive text.
    """

    def __init__(self, parent=None, placeholderText=""):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param placeholderText text to be shown on inactivity
        @type str
        """
        super().__init__(parent)

        self.setMinimumHeight(22)

        self.setPlaceholderText(placeholderText)

        self.__mainLayout = QHBoxLayout(self)
        self.__mainLayout.setContentsMargins(0, 0, 0, 0)
        self.__mainLayout.setSpacing(0)

        self.__leftMargin = 0
        self.__leftWidget = EricLineEditSideWidget(self)
        self.__leftWidget.resize(0, 0)
        self.__leftLayout = QHBoxLayout(self.__leftWidget)
        self.__leftLayout.setContentsMargins(0, 0, 2, 0)
        if QApplication.isRightToLeft():
            self.__leftLayout.setDirection(QBoxLayout.Direction.RightToLeft)
        else:
            self.__leftLayout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.__leftLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        self.__rightWidget = EricLineEditSideWidget(self)
        self.__rightWidget.resize(0, 0)
        self.__rightLayout = QHBoxLayout(self.__rightWidget)
        self.__rightLayout.setContentsMargins(0, 0, 2, 0)
        if self.isRightToLeft():
            self.__rightLayout.setDirection(QBoxLayout.Direction.RightToLeft)
        else:
            self.__rightLayout.setDirection(QBoxLayout.Direction.LeftToRight)

        horizontalSpacer = QSpacerItem(
            0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.__mainLayout.addWidget(
            self.__leftWidget,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
        )
        self.__mainLayout.addItem(horizontalSpacer)
        self.__mainLayout.addWidget(
            self.__rightWidget,
            0,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
        )
        if self.isRightToLeft():
            self.__mainLayout.setDirection(QBoxLayout.Direction.RightToLeft)
        else:
            self.__mainLayout.setDirection(QBoxLayout.Direction.LeftToRight)

        self.setWidgetSpacing(3)
        self.__leftWidget.sizeHintChanged.connect(self._updateTextMargins)
        self.__rightWidget.sizeHintChanged.connect(self._updateTextMargins)

    def setLeftMargin(self, margin):
        """
        Public method to set the left margin.

        @param margin left margin in pixel
        @type int
        """
        self.__leftMargin = margin

    def leftMargin(self):
        """
        Public method to get the size of the left margin.

        @return left margin in pixel
        @rtype int
        """
        return self.__leftMargin

    def event(self, evt):
        """
        Public method to handle events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating, whether the event was recognized
        @rtype bool
        """
        if evt.type() == QEvent.Type.LayoutDirectionChange:
            if self.isRightToLeft():
                self.__mainLayout.setDirection(QBoxLayout.Direction.RightToLeft)
                self.__leftLayout.setDirection(QBoxLayout.Direction.RightToLeft)
                self.__rightLayout.setDirection(QBoxLayout.Direction.RightToLeft)
            else:
                self.__mainLayout.setDirection(QBoxLayout.Direction.LeftToRight)
                self.__leftLayout.setDirection(QBoxLayout.Direction.LeftToRight)
                self.__rightLayout.setDirection(QBoxLayout.Direction.LeftToRight)
        return QLineEdit.event(self, evt)

    def _updateTextMargins(self):
        """
        Protected slot to update the text margins.
        """
        left = (
            self.__leftWidget.sizeHint().width()
            if self.__leftMargin == 0
            else self.__leftMargin
        )
        right = self.__rightWidget.sizeHint().width()
        top = 0
        bottom = 0
        self.setTextMargins(left, top, right, bottom)

    def addWidget(self, widget, position):
        """
        Public method to add a widget to a side.

        @param widget reference to the widget to add
        @type QWidget
        @param position position to add to
        @type EricLineEditSide
        """
        if widget is None:
            return

        if self.isRightToLeft():
            if position == EricLineEditSide.LEFT:
                position = EricLineEditSide.RIGHT
            else:
                position = EricLineEditSide.LEFT
        if position == EricLineEditSide.LEFT:
            self.__leftLayout.addWidget(widget)
        else:
            self.__rightLayout.insertWidget(1, widget)

    def removeWidget(self, widget):
        """
        Public method to remove a widget from a side.

        @param widget reference to the widget to remove
        @type QWidget
        """
        if widget is None:
            return

        self.__leftLayout.removeWidget(widget)
        self.__rightLayout.removeWidget(widget)
        widget.hide()

    def widgetSpacing(self):
        """
        Public method to get the side widget spacing.

        @return side widget spacing
        @rtype int
        """
        return self.__leftLayout.spacing()

    def setWidgetSpacing(self, spacing):
        """
        Public method to set the side widget spacing.

        @param spacing side widget spacing
        @type int
        """
        self.__leftLayout.setSpacing(spacing)
        self.__rightLayout.setSpacing(spacing)
        self._updateTextMargins()

    def textMargin(self, position):
        """
        Public method to get the text margin for a side.

        @param position side to get margin for
        @type EricLineEditSide
        @return text margin
        @rtype int
        """
        spacing = self.__rightLayout.spacing()
        w = 0
        w = (
            self.__leftWidget.sizeHint().width()
            if position == EricLineEditSide.LEFT
            else self.__rightWidget.sizeHint().width()
        )
        if w == 0:
            return 0
        return w + spacing * 2


class EricClearableLineEdit(EricLineEdit):
    """
    Class implementing a line edit widget showing some inactive text and a
    clear button, if it has some contents.
    """

    def __init__(self, parent=None, placeholderText=""):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param placeholderText text to be shown on inactivity
        @type str
        """
        super().__init__(parent, placeholderText)

        self.setClearButtonEnabled(True)
