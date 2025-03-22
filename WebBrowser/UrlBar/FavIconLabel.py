# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the label to show the web site icon.
"""

from PyQt6.QtCore import QMimeData, QPoint, Qt
from PyQt6.QtGui import QDrag, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel


class FavIconLabel(QLabel):
    """
    Class implementing the label to show the web site icon.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__browser = None
        self.__dragStartPos = QPoint()

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMinimumSize(16, 16)
        self.resize(16, 16)

        self.__browserIconChanged()

    def __browserIconChanged(self):
        """
        Private slot to set the icon.
        """
        if self.__browser:
            self.setPixmap(self.__browser.icon().pixmap(16, 16))

    def __clearIcon(self):
        """
        Private slot to clear the icon.
        """
        self.setPixmap(QPixmap())

    def setBrowser(self, browser):
        """
        Public method to set the browser connection.

        @param browser reference to the browser widget
        @type WebBrowserView
        """
        self.__browser = browser
        self.__browser.loadFinished.connect(self.__browserIconChanged)
        self.__browser.faviconChanged.connect(self.__browserIconChanged)
        self.__browser.loadStarted.connect(self.__clearIcon)

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse press events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.__dragStartPos = evt.position().toPoint()
        super().mousePressEvent(evt)

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse release events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.__showPopup(evt.globalPosition().toPoint())
        super().mouseReleaseEvent(evt)

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse move events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if (
            evt.button() == Qt.MouseButton.LeftButton
            and (
                (evt.position().toPoint() - self.__dragStartPos).manhattanLength()
                > QApplication.startDragDistance()
            )
            and self.__browser is not None
        ):
            drag = QDrag(self)
            mimeData = QMimeData()
            title = self.__browser.title()
            if title == "":
                title = str(self.__browser.url().toEncoded(), encoding="utf-8")
            mimeData.setText(title)
            mimeData.setUrls([self.__browser.url()])
            p = self.pixmap()
            if p:
                drag.setPixmap(p)
            drag.setMimeData(mimeData)
            drag.exec()

    def __showPopup(self, pos):
        """
        Private method to show the site info popup.

        @param pos position the popup should be shown at
        @type QPoint
        """
        from ..SiteInfo.SiteInfoWidget import SiteInfoWidget

        if self.__browser is None:
            return

        url = self.__browser.url()
        if url.isValid() and url.scheme() not in ["eric", "about", "data", "chrome"]:
            info = SiteInfoWidget(self.__browser, self)
            info.showAt(pos)
