# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a specialized tool button subclass.
"""

import enum

from PyQt6.QtCore import QSize, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QStyle,
    QStyleOption,
    QStyleOptionToolButton,
    QToolButton,
)


class EricToolButtonOptions(enum.IntEnum):
    """
    Class defining the tool button options.
    """

    DEFAULT = 0
    SHOW_MENU_INSIDE = 1
    TOOLBAR_LOOKUP = 2


class EricToolButton(QToolButton):
    """
    Class implementing a specialized tool button subclass.

    @signal aboutToShowMenu() emitted before the tool button menu is shown
    @signal aboutToHideMenu() emitted before the tool button menu is hidden
    @signal middleClicked() emitted when the middle mouse button was clicked
    @signal controlClicked() emitted when the left mouse button was
        clicked while pressing the Ctrl key
    @signal doubleClicked() emitted when the left mouse button was
        double clicked
    """

    aboutToShowMenu = pyqtSignal()
    aboutToHideMenu = pyqtSignal()
    middleClicked = pyqtSignal()
    controlClicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setMinimumWidth(16)

        self.__menu = None
        self.__options = EricToolButtonOptions.DEFAULT

        self.__badgeLabel = QLabel(self)
        font = self.__badgeLabel.font()
        font.setPixelSize(int(self.__badgeLabel.height() / 2.5))
        self.__badgeLabel.setFont(font)
        self.__badgeLabel.hide()

        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)

        self.__pressTimer = QTimer()
        self.__pressTimer.setSingleShot(True)
        self.__pressTimer.setInterval(
            QApplication.style().styleHint(
                QStyle.StyleHint.SH_ToolButton_PopupDelay, opt, self
            )
        )
        self.__pressTimer.timeout.connect(self.__showMenu)

    ##################################################################
    ## Menu handling methods below.
    ##
    ## The menu is handled in EricToolButton and is not passed to
    ## QToolButton. No menu indicator will be shown in the button.
    ##################################################################

    def menu(self):
        """
        Public method to get a reference to the tool button menu.

        @return reference to the tool button menu
        @rtype QMenu
        """
        return self.__menu

    def setMenu(self, menu):
        """
        Public method to set the tool button menu.

        @param menu reference to the tool button menu
        @type QMenu
        """
        if menu is None:
            # show the default tool button context menu
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        else:
            if self.__menu:
                self.__menu.aboutToHide.disconnect(self.__menuAboutToHide)

            self.__menu = menu
            self.__menu.aboutToHide.connect(self.__menuAboutToHide)

            # prevent showing the context menu and the tool button menu
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def showMenuInside(self):
        """
        Public method to check, if the menu edge shall be aligned with
        the button.

        @return flag indicating that the menu edge shall be aligned
        @rtype bool
        """
        return bool(self.__options & EricToolButtonOptions.SHOW_MENU_INSIDE)

    def setShowMenuInside(self, enable):
        """
        Public method to set a flag to show the menu edge aligned with
        the button.

        @param enable flag indicating to align the menu edge to the button
        @type bool
        """
        if enable:
            self.__options |= EricToolButtonOptions.SHOW_MENU_INSIDE
        else:
            self.__options &= ~EricToolButtonOptions.SHOW_MENU_INSIDE

    @pyqtSlot()
    def __showMenu(self):
        """
        Private slot to show the tool button menu.
        """
        if self.__menu is None or self.__menu.isVisible():
            return

        self.aboutToShowMenu.emit()

        if self.__options & EricToolButtonOptions.SHOW_MENU_INSIDE:
            pos = self.mapToGlobal(self.rect().bottomRight())
            if QApplication.layoutDirection() == Qt.LayoutDirection.RightToLeft:
                pos.setX(pos.x() - self.rect().width())
            else:
                pos.setX(pos.x() - self.__menu.sizeHint().width())
        else:
            pos = self.mapToGlobal(self.rect().bottomLeft())

        self.__menu.popup(pos)

    @pyqtSlot()
    def __menuAboutToHide(self):
        """
        Private slot to handle the tool button menu about to be hidden.
        """
        self.setDown(False)
        self.aboutToHideMenu.emit()

    ##################################################################
    ## Methods to handle the tool button look
    ##################################################################

    def toolbarButtonLook(self):
        """
        Public method to check, if the button has the toolbar look.

        @return flag indicating toolbar look
        @rtype bool
        """
        return bool(self.__options & EricToolButtonOptions.TOOLBAR_LOOKUP)

    def setToolbarButtonLook(self, enable):
        """
        Public method to set the toolbar look state.

        @param enable flag indicating toolbar look
        @type bool
        """
        if enable:
            self.__options |= EricToolButtonOptions.TOOLBAR_LOOKUP

            opt = QStyleOption()
            opt.initFrom(self)
            size = self.style().pixelMetric(
                QStyle.PixelMetric.PM_ToolBarIconSize, opt, self
            )
            self.setIconSize(QSize(size, size))
        else:
            self.__options &= ~EricToolButtonOptions.TOOLBAR_LOOKUP

        self.setProperty("toolbar-look", enable)
        self.style().unpolish(self)
        self.style().polish(self)

    ##################################################################
    ## Methods to handle some event types
    ##################################################################

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse press events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if self.popupMode() == QToolButton.ToolButtonPopupMode.DelayedPopup:
            self.__pressTimer.start()

        if (
            evt.buttons() == Qt.MouseButton.LeftButton
            and self.__menu is not None
            and (self.popupMode() == QToolButton.ToolButtonPopupMode.InstantPopup)
        ) or (evt.buttons() == Qt.MouseButton.RightButton and self.__menu is not None):
            self.setDown(True)
            self.__showMenu()
        else:
            super().mousePressEvent(evt)

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse release events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        self.__pressTimer.stop()

        if evt.button() == Qt.MouseButton.MiddleButton and self.rect().contains(
            evt.position().toPoint()
        ):
            self.middleClicked.emit()
            self.setDown(False)
        elif (
            evt.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(evt.position().toPoint())
            and evt.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.controlClicked.emit()
            self.setDown(False)
        else:
            super().mouseReleaseEvent(evt)

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method to handle mouse double click events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        super().mouseDoubleClickEvent(evt)

        self.__pressTimer.stop()

        if evt.buttons() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()

    ##################################################################
    ## Methods to handle the tool button badge
    ##################################################################

    def setBadgeText(self, text):
        """
        Public method to set the badge text.

        @param text badge text to be set
        @type str
        """
        if text:
            self.__badgeLabel.setText(text)
            self.__badgeLabel.resize(self.__badgeLabel.sizeHint())
            self.__badgeLabel.move(self.width() - self.__badgeLabel.width(), 0)
            self.__badgeLabel.show()
        else:
            self.__badgeLabel.clear()
            self.__badgeLabel.hide()

    def badgeText(self):
        """
        Public method to get the badge text.

        @return badge text
        @rtype str
        """
        return self.__badgeLabel.text()
