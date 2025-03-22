# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a bar widget showing just icons.
"""

import contextlib

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QCursor, QIcon, QPalette
from PyQt6.QtWidgets import QWIDGETSIZE_MAX, QBoxLayout, QMenu, QWidget

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp

from .EricClickableLabel import EricClickableLabel


class EricIconBar(QWidget):
    """
    Class implementing a bar widget showing just icons.

    @signal currentChanged(index) emitted to indicate a change of the current
        index
    @signal currentClicked(index) emitted to indicate, that the current icon
        was clicked
    @signal emptyClicked() emitted to indicate a mouse click on the empty part
        of the icon bar
    """

    BarSizes = {
        # tuples with (icon size, border size, translated size string)
        "xs": (16, 1, QCoreApplication.translate("EricIconBar", "extra small (16 px)")),
        "sm": (22, 1, QCoreApplication.translate("EricIconBar", "small (22 px)")),
        "md": (32, 2, QCoreApplication.translate("EricIconBar", "medium (32 px)")),
        "lg": (48, 2, QCoreApplication.translate("EricIconBar", "large (48 px)")),
        "xl": (64, 3, QCoreApplication.translate("EricIconBar", "extra large (64 px)")),
        "xxl": (96, 3, QCoreApplication.translate("EricIconBar", "very large (96 px)")),
    }
    DefaultBarSize = "md"

    MoreLabelAspect = 36 / 96

    MenuStyleSheetTemplate = (
        "QMenu {{ background-color: {0}; "
        "selection-background-color: {1}; "
        "border: 1px solid; }}"
    )
    WidgetStyleSheetTemplate = "QWidget {{ background-color: {0}; }}"
    LabelStyleSheetTemplate = "QLabel {{ background-color: {0}; }}"

    currentChanged = pyqtSignal(int)
    currentClicked = pyqtSignal(int)
    emptyClicked = pyqtSignal()

    def __init__(
        self, orientation=Qt.Orientation.Horizontal, barSize=DefaultBarSize, parent=None
    ):
        """
        Constructor

        @param orientation orientation for the widget
        @type Qt.Orientation
        @param barSize size category for the bar (one of 'xs', 'sm', 'md',
            'lg', 'xl', 'xxl')
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        try:
            self.__barSize, self.__borderSize = EricIconBar.BarSizes[barSize][:2]
            self.__barSizeKey = barSize
        except KeyError:
            self.__barSize, self.__borderSize = EricIconBar.BarSizes[
                EricIconBar.DefaultBarSize
            ][:2]
        self.__fixedHeightWidth = self.__barSize + 2 * self.__borderSize
        self.__minimumHeightWidth = (
            int(self.__barSize * self.MoreLabelAspect) + 2 * self.__borderSize
        )

        # set initial values
        self.__color = QColor("#008800")
        self.__orientation = Qt.Orientation.Horizontal
        self.__currentIndex = -1
        self.__icons = []

        # initialize with horizontal layout and change later if needed
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(self.__fixedHeightWidth)
        self.setMinimumWidth(self.__minimumHeightWidth)

        self.__layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.__layout.setContentsMargins(
            self.__borderSize, self.__borderSize, self.__borderSize, self.__borderSize
        )

        self.__layout.addStretch()

        self.setLayout(self.__layout)

        if orientation != self.__orientation:
            self.setOrientation(orientation)

        self.setColor(self.__color)

        self.__createAndAddMoreLabel()

        self.__adjustIconLabels()

    def setOrientation(self, orientation):
        """
        Public method to set the widget orientation.

        @param orientation orientation to be set
        @type Qt.Orientation
        """
        # reset list widget size constraints
        self.setFixedSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)

        # remove the 'More' icon
        itm = self.__layout.takeAt(self.__layout.count() - 1)
        itm.widget().deleteLater()
        del itm

        if orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(self.__fixedHeightWidth)
            self.setMinimumWidth(self.__minimumHeightWidth)
            self.__layout.setDirection(QBoxLayout.Direction.LeftToRight)
        elif orientation == Qt.Orientation.Vertical:
            self.setFixedWidth(self.__fixedHeightWidth)
            self.setMinimumHeight(self.__minimumHeightWidth)
            self.__layout.setDirection(QBoxLayout.Direction.TopToBottom)

        self.__orientation = orientation

        self.__createAndAddMoreLabel()

        self.__adjustIconLabels()

    def orientation(self):
        """
        Public method to get the orientation of the widget.

        @return orientation of the widget
        @rtype Qt.Orientation
        """
        return self.__orientation

    def setBarSize(self, barSize):
        """
        Public method to set the icon bar size.

        @param barSize size category for the bar (one of 'xs', 'sm', 'md',
            'lg', 'xl', 'xxl')
        @type str
        """
        # remove the 'More' icon
        itm = self.__layout.takeAt(self.__layout.count() - 1)
        itm.widget().deleteLater()
        del itm

        self.__barSize, self.__borderSize = EricIconBar.BarSizes[barSize][:2]
        self.__barSizeKey = barSize
        self.__fixedHeightWidth = self.__barSize + 2 * self.__borderSize
        self.__minimumHeightWidth = (
            int(self.__barSize * self.MoreLabelAspect) + 2 * self.__borderSize
        )

        if self.__orientation == Qt.Orientation.Horizontal:
            self.setFixedHeight(self.__fixedHeightWidth)
            self.setMinimumWidth(self.__minimumHeightWidth)
        elif self.__orientation == Qt.Orientation.Vertical:
            self.setFixedWidth(self.__fixedHeightWidth)
            self.setMinimumHeight(self.__minimumHeightWidth)

        self.__layout.setContentsMargins(
            self.__borderSize, self.__borderSize, self.__borderSize, self.__borderSize
        )

        for index, icon in enumerate(self.__icons):
            iconLabel = self.__layout.itemAt(index)
            if iconLabel:
                widget = iconLabel.widget()
                widget.setFixedSize(self.__barSize, self.__barSize)
                widget.setPixmap(icon.pixmap(self.__barSize, self.__barSize))

        self.__createAndAddMoreLabel()

        self.__adjustIconLabels()

    def barSize(self):
        """
        Public method to get the icon bar size.

        @return barSize size category for the bar (one of 'xs', 'sm', 'md',
            'lg', 'xl', 'xxl')
        @rtype str
        """
        return self.__barSizeKey

    def setColor(self, color):
        """
        Public method to set the color of the widget.

        @param color color of the widget
        @type QColor
        """
        self.__color = color
        self.__highlightColor = color.darker()

        self.setStyleSheet(EricIconBar.WidgetStyleSheetTemplate.format(color.name()))

        label = self.__layout.itemAt(self.__currentIndex)
        if label:
            widget = label.widget()
            if widget:
                widget.setStyleSheet(
                    EricIconBar.LabelStyleSheetTemplate.format(
                        self.__highlightColor.name()
                    )
                )

    def color(self):
        """
        Public method to return the current color.

        @return current color
        @rtype QColor
        """
        return self.__color

    def __createIcon(self, icon, label=""):
        """
        Private method to creat an icon label.

        @param icon reference to the icon
        @type QIcon
        @param label label text to be shown as a tooltip (defaults to "")
        @type str (optional)
        @return created and connected label
        @rtype EricClickableLabel
        """
        iconLabel = EricClickableLabel(self)
        iconLabel.setFixedSize(self.__barSize, self.__barSize)
        iconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        iconLabel.setPixmap(icon.pixmap(self.__barSize, self.__barSize))
        if label:
            iconLabel.setToolTip(label)

        iconLabel.clicked.connect(lambda: self.__iconClicked(iconLabel))

        return iconLabel

    def __createAndAddMoreLabel(self):
        """
        Private method to create the label to be shown for too many icons.
        """
        self.__moreLabel = EricClickableLabel(self)
        self.__moreLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.__orientation == Qt.Orientation.Horizontal:
            self.__moreLabel.setFixedSize(
                int(self.__barSize * self.MoreLabelAspect), self.__barSize
            )
            self.__moreLabel.setPixmap(
                EricPixmapCache.getIcon("sbDotsH96").pixmap(
                    int(self.__barSize * self.MoreLabelAspect), self.__barSize
                )
            )
        else:
            self.__moreLabel.setFixedSize(
                self.__barSize, int(self.__barSize * self.MoreLabelAspect)
            )
            self.__moreLabel.setPixmap(
                EricPixmapCache.getIcon("sbDotsV96").pixmap(
                    self.__barSize, int(self.__barSize * self.MoreLabelAspect)
                )
            )

        self.__layout.addWidget(self.__moreLabel)

        self.__moreLabel.clicked.connect(self.__moreLabelClicked)

    def addIcon(self, icon, label=""):
        """
        Public method to add an icon to the bar.

        @param icon reference to the icon
        @type QIcon
        @param label label text to be shown as a tooltip (defaults to "")
        @type str (optional)
        """
        # the stretch item is always the last one
        self.insertIcon(self.count(), icon, label=label)

    def insertIcon(self, index, icon, label=""):
        """
        Public method to insert an icon into the bar.

        @param index position to insert the icon at
        @type int
        @param icon reference to the icon
        @type QIcon
        @param label label text to be shown as a tooltip (defaults to "")
        @type str (optional)
        """
        iconLabel = self.__createIcon(icon, label=label)
        self.__layout.insertWidget(index, iconLabel)
        self.__icons.insert(index, QIcon(icon))

        if self.__currentIndex < 0:
            self.setCurrentIndex(index)
        elif index <= self.__currentIndex:
            self.setCurrentIndex(self.__currentIndex + 1)

        self.__adjustIconLabels()

    def removeIcon(self, index):
        """
        Public method to remove an icon from the bar.

        @param index index of the icon to be removed
        @type int
        """
        label = self.__layout.itemAt(index)
        if label:
            with contextlib.suppress(IndexError):
                del self.__icons[index]
            itm = self.__layout.takeAt(index)
            itm.widget().deleteLater()
            del itm

            if index == self.__currentIndex:
                self.setCurrentIndex(index)
            elif index < self.__currentIndex:
                self.setCurrentIndex(self.__currentIndex - 1)

            self.__adjustIconLabels()

    def setIcon(self, index, icon):
        """
        Public method to set the icon at the given index.

        @param index icon index
        @type int
        @param icon reference to the icon
        @type QIcon
        """
        labelItem = self.__layout.itemAt(index)
        if labelItem:
            labelItem.widget().setPixmap(icon.pixmap(self.__barSize, self.__barSize))

    @pyqtSlot()
    def __iconClicked(self, label):
        """
        Private slot to handle an icon been clicked.

        @param label reference to the clicked label
        @type EricClickableLabel
        """
        index = self.__layout.indexOf(label)
        if index >= 0:
            if index == self.__currentIndex:
                self.currentClicked.emit(self.__currentIndex)
            else:
                self.setCurrentIndex(index)

    def setCurrentIndex(self, index):
        """
        Public method to set the current index.

        @param index current index to be set
        @type int
        """
        if index >= self.count():
            index = -1

        if index != self.__currentIndex and index >= 0:
            # reset style of previous current icon
            oldLabel = self.__layout.itemAt(self.__currentIndex)
            if oldLabel:
                widget = oldLabel.widget()
                if widget is not None:
                    widget.setStyleSheet("")

            # set style of new current icon
            newLabel = self.__layout.itemAt(index)
            if newLabel:
                newLabel.widget().setStyleSheet(
                    EricIconBar.LabelStyleSheetTemplate.format(
                        self.__highlightColor.name()
                    )
                )

            self.__currentIndex = index
            self.currentChanged.emit(self.__currentIndex)

    def currentIndex(self):
        """
        Public method to get the current index.

        @return current index
        @rtype int
        """
        return self.__currentIndex

    def count(self):
        """
        Public method to get the number of icon labels.

        @return number of icon labels
        @rtype int
        """
        return len(self.__icons)

    def wheelEvent(self, evt):
        """
        Protected method to handle a wheel event.

        @param evt reference to the wheel event
        @type QWheelEvent
        """
        delta = evt.angleDelta().y()
        if delta > 0:
            self.previousIcon()
        else:
            self.nextIcon()

    @pyqtSlot()
    def previousIcon(self):
        """
        Public slot to set the icon before the current one.
        """
        index = self.__currentIndex - 1
        if index < 0:
            # wrap around
            index = self.count() - 1

        self.setCurrentIndex(index)

    @pyqtSlot()
    def nextIcon(self):
        """
        Public slot to set the icon after the current one.
        """
        index = self.__currentIndex + 1
        if index == self.count():
            # wrap around
            index = 0

        self.setCurrentIndex(index)

    @pyqtSlot()
    def __moreLabelClicked(self):
        """
        Private slot to handle a click onto the 'More' label.
        """
        menu = QMenu(self)
        baseColor = ericApp().palette().color(QPalette.ColorRole.Base)
        highlightColor = ericApp().palette().color(QPalette.ColorRole.Highlight)
        menu.setStyleSheet(
            EricIconBar.MenuStyleSheetTemplate.format(
                baseColor.name(), highlightColor.name()
            )
        )

        for index in range(self.count()):
            iconLabel = self.__layout.itemAt(index)
            if iconLabel:
                widget = iconLabel.widget()
                if not widget.isVisible():
                    act = menu.addAction(widget.toolTip())
                    act.setData(index)

        selectedAction = menu.exec(QCursor.pos())
        if selectedAction is not None:
            index = selectedAction.data()
            if index >= 0:
                if index == self.__currentIndex:
                    self.currentClicked.emit(self.__currentIndex)
                else:
                    self.setCurrentIndex(index)

    def resizeEvent(self, evt):
        """
        Protected method to handle resizing of the icon bar.

        @param evt reference to the event object
        @type QResizeEvent
        """
        self.__adjustIconLabels()

    def __adjustIconLabels(self):
        """
        Private method to adjust the visibility of the icon labels.
        """
        size = (
            self.width()
            if self.orientation() == Qt.Orientation.Horizontal
            else self.height()
        ) - 2 * self.__borderSize

        iconsSize = self.count() * self.__barSize

        if size < iconsSize:
            self.__moreLabel.show()
            iconsSize += int(self.__barSize * self.MoreLabelAspect)
            for index in range(self.count() - 1, -1, -1):
                iconLabel = self.__layout.itemAt(index)
                if iconLabel:
                    if size < iconsSize:
                        iconLabel.widget().hide()
                        iconsSize -= self.__barSize
                    else:
                        iconLabel.widget().show()
        else:
            self.__moreLabel.hide()
            for index in range(self.count()):
                iconLabel = self.__layout.itemAt(index)
                if iconLabel:
                    iconLabel.widget().show()

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle a click on the empty space.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        self.emptyClicked.emit()
